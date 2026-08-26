"""Setup in, verdict out.

**An addition to the BUILD_PROMPT scaffold**, and here is why: Part 10 asks for integration
tests -- "a fabricated screenshot plus fixture data produces a well-formed TRADE", "chop
produces NO TRADE and names the veto", "missing data produces NO TRADE, never a fabricated
level". None of those can be tested if the verdict only ever exists as prose in a chat reply.
So the grading, the guarding, the sizing and the rendering live here, in code, under test.

The division of labour:

* **The model** reads the screenshot (perception) and proposes a ``Setup`` -- direction, the
  zone it is at, what confirmed it, and the trigger/stop/target geometry.
* **This module** grades it, guards it, sizes it, picks the verdict and renders it.

That way the honesty rules are enforced by something that cannot be talked out of them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

# Running as a script (``python3 tools/grade.py``) puts tools/ on sys.path, not the repo root,
# so the package imports below would fail. Put the root on the path first.
if __package__ in (None, ""):  # pragma: no cover
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from tools import guards as G
from tools import market
from tools.vision import Reconciliation, Status

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")

#: Guards whose veto expires on a known clock -- these become WAIT, not NO TRADE.
TIMED_GUARDS = {2: "opening lockout", 3: "event lockout", 6: "cooldown"}


def both_tz(dt: datetime) -> str:
    return f"{dt.astimezone(CT):%H:%M} CT / {dt.astimezone(ET):%H:%M} ET"


@dataclass
class Setup:
    """What the model proposes, from the chart. Geometry only -- no verdict."""

    direction: str                     # "long" or "short"
    entry_low: float
    entry_high: float
    stop: float
    target1: float
    target2: Optional[float] = None
    zone: str = ""                     # the level it is trading at, e.g. "prior day high 767.30"
    zone_quality: str = "minor"        # "major" | "minor" | "none"
    confirmation: str = ""             # "pin bar" | "engulfing" | "reclaim" | "" if none
    confirmed_closed: bool = False     # False when the signal candle is still printing
    notes: str = ""

    @property
    def risk(self) -> float:
        return abs(self.entry_high - self.stop) if self.direction.startswith("l") \
            else abs(self.stop - self.entry_low)

    @property
    def reward(self) -> float:
        ref = self.entry_high if self.direction.startswith("l") else self.entry_low
        return abs(self.target1 - ref)

    @property
    def rr(self) -> float:
        return self.reward / self.risk if self.risk else 0.0


@dataclass
class Decision:
    verdict: str                       # TRADE | NO TRADE | WAIT
    ticker: str
    direction: str = ""
    grade: str = "C"
    why: list[str] = field(default_factory=list)
    against: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    guard_vetoes: list[G.GuardResult] = field(default_factory=list)
    wait_until: Optional[datetime] = None
    wait_for: list[str] = field(default_factory=list)
    setup: Optional[Setup] = None
    contracts: int = 0
    contract_note: str = ""
    reconciliation: Optional[Reconciliation] = None
    no_data_reason: str = ""


# --------------------------------------------------------------------------------------
# the rubric
# --------------------------------------------------------------------------------------

def stack_alignment(ind, direction: str) -> tuple[int, str]:
    """How many of the five Trycon lines price sits on the right side of."""
    lines = [ind.ema9, ind.ema21, ind.ema50, ind.ema200, ind.sma200]
    lines = [x for x in lines if x is not None and not math.isnan(x)]
    if not lines:
        return 0, "no moving average values"
    if direction.startswith("l"):
        agree = sum(1 for x in lines if ind.last > x)
    else:
        agree = sum(1 for x in lines if ind.last < x)
    total = len(lines)
    if agree == total:
        return 25, f"price on the right side of all {total} lines — clean stack"
    if agree >= total - 1:
        return 18, f"price above/below {agree} of {total} lines"
    if agree >= total - 2:
        return 10, f"price on the right side of only {agree} of {total} lines"
    return 0, f"stack argues the other way — {agree} of {total}"


def session_window_score(now: datetime) -> tuple[int, str]:
    et = now.astimezone(ET)
    minutes = et.hour * 60 + et.minute
    if minutes < 9 * 60 + 45:
        return 0, "the open — noise"
    if minutes < 11 * 60 + 30:
        return 10, "prime window"
    if minutes < 13 * 60 + 30:
        return 5, "midday tape"
    if minutes < 15 * 60:
        return 3, "afternoon, theta accelerating"
    return 0, "past the entry cutoff"


def evidence(setup: Setup, ind, now: datetime,
             lessons_against: Sequence[str] = ()) -> tuple[list[str], list[str]]:
    """The WHY and AGAINST lines, as plain evidence.

    **There is no conviction score.** CJ dropped it: ``06-mentor-engine.md`` forbids a
    confidence percentage, and a number out of 100 sitting next to a trade reads as a
    likelihood no matter how it is labelled. The grade (A/B/C) carries the quality judgement;
    these lines carry the reasons, each one checkable. See ``_INDEX.md`` contradiction 4.
    """
    supporting: list[str] = []
    against: list[str] = []

    stack_pts, stack_why = stack_alignment(ind, setup.direction)
    (supporting if stack_pts >= 18 else against).append(stack_why)

    if setup.zone and setup.zone_quality != "none":
        supporting.append(f"at {setup.zone} ({setup.zone_quality} level)")
    else:
        against.append("not at a real zone — mid-range entries are not setups")

    if setup.confirmation and setup.confirmed_closed:
        supporting.append(f"closed {setup.confirmation} at the zone")
    elif setup.confirmation:
        against.append(f"{setup.confirmation} is still printing — not confirmed until it closes")
    else:
        against.append("no closed-candle confirmation")

    rr = setup.rr
    if rr >= 2.0:
        supporting.append(f"{rr:.2f}R of room to target 1")
    elif rr >= 1.5:
        supporting.append(f"{rr:.2f}R to target 1 — enough, but not generous")
    else:
        against.append(f"only {rr:.2f}R to target 1, under the 1.5R floor")

    window_pts, window_why = session_window_score(now)
    (supporting if window_pts >= 10 else against).append(window_why)

    for lesson in lessons_against:
        against.append(f"lesson argues against: {lesson}")

    return supporting, against


def grade(setup: Setup, ind, now: datetime, lessons_against: Sequence[str] = ()) -> tuple[str, list[str]]:
    """A / B / C, and what is missing. ``01-decision-engine.md`` Step E."""
    missing: list[str] = []

    stack_score, _ = stack_alignment(ind, setup.direction)
    if stack_score < 25:
        missing.append("clean five-line stack")
    if setup.zone_quality == "none" or not setup.zone:
        missing.append("a real zone")
    if not (setup.confirmation and setup.confirmed_closed):
        missing.append("closed-candle confirmation")
    if setup.rr < 1.5:
        missing.append(f"room to target ({setup.rr:.2f}R, needs 1.5R)")
    if session_window_score(now)[0] < 10:
        missing.append("prime session window")

    if lessons_against:
        letter = "C" if len(missing) >= 2 else "B"
        return letter, missing + [f"lesson argues against: {'; '.join(lessons_against)}"]

    if not missing:
        return "A", []
    if len(missing) == 1:
        return "B", missing
    return "C", missing


# --------------------------------------------------------------------------------------
# sizing
# --------------------------------------------------------------------------------------

def risk_budget(cfg: dict, grade_letter: str) -> float:
    """Dollar risk for this grade.

    CJ's rule, in his words: *"most of the time $100, but if the trade is really good you can
    get a little more — $350."* Grade A needs all five legs clean, including the prime session
    window, so it is the uncommon case and $100 stays the default.

    **1R is always ``unit_r_usd``**, regardless of what this returns. The R accounting unit has
    to stay fixed or the daily loss limit, the ledger and every lesson stop being comparable.
    A max-size A therefore risks 3.5R, not 1R.
    """
    unit = cfg["risk"]["unit_r_usd"]
    multiplier = cfg["risk"]["grade_risk_multiplier"].get(grade_letter, 1.0)
    return min(unit * multiplier, cfg["risk"]["max_risk_usd"])


def size_position(setup: Setup, cfg: dict, grade_letter: str,
                  premium: Optional[float] = None,
                  premium_at_stop: Optional[float] = None) -> tuple[int, str]:
    """Contract count from the risk budget, or an honest refusal to guess.

    Without a chain there is no premium, and a price chart cannot supply one
    (``02-trycon-mas.md``). In that case: **1 contract and say so**, rather than inventing a
    number that looks precise.
    """
    budget = risk_budget(cfg, grade_letter)
    unit = cfg["risk"]["unit_r_usd"]

    if premium is None or premium_at_stop is None:
        return 1, (
            f"Size it off your chain — I can't see a bid/ask from a price chart. "
            f"Budget is ${budget:,.0f} on this {grade_letter} ({budget / unit:.1f}R)."
        )

    per_contract = max(0.01, (premium - premium_at_stop)) * 100
    n = int(budget // per_contract)
    if n < 1:
        return 0, (
            f"1 contract risks ~${per_contract:,.0f}, over your ${budget:,.0f} budget. "
            f"Skip it or cut size elsewhere — I'm not rounding you into a bigger position."
        )
    return n, (
        f"~${per_contract:,.0f} risk per contract against a ${budget:,.0f} budget "
        f"({budget / unit:.1f}R on {'an' if grade_letter == 'A' else 'a'} {grade_letter})"
    )


# --------------------------------------------------------------------------------------
# the decision
# --------------------------------------------------------------------------------------

def decide(
    ticker: str,
    setup: Optional[Setup],
    ind,
    now: datetime,
    cfg: dict,
    guard_ctx: Optional[G.GuardContext] = None,
    reconciliation: Optional[Reconciliation] = None,
    lessons_against: Sequence[str] = (),
    no_data_reason: str = "",
    premium: Optional[float] = None,
    premium_at_stop: Optional[float] = None,
) -> Decision:
    """Run the engine and the guards, then pick one of exactly three verdicts."""

    # --- no data beats everything. Never fabricate a level.
    if no_data_reason or ind is None:
        return Decision(
            verdict="NO TRADE", ticker=ticker,
            why=[f"No usable price data: {no_data_reason or 'no bars available'}"],
            no_data_reason=no_data_reason or "no bars available",
        )

    if reconciliation is not None and reconciliation.status is Status.STALE_SCREENSHOT:
        return Decision(
            verdict="WAIT", ticker=ticker, reconciliation=reconciliation,
            wait_until=now,
            wait_for=["a fresh screenshot — this one does not match the bars"],
            why=[reconciliation.message],
        )

    if setup is None:
        return Decision(
            verdict="NO TRADE", ticker=ticker, reconciliation=reconciliation,
            why=["No setup on this chart."], missing=["a setup"],
        )

    letter, missing = grade(setup, ind, now, lessons_against)
    supporting, against = evidence(setup, ind, now, lessons_against)

    ctx = guard_ctx or G.GuardContext(now=now)
    ctx.now = now
    if math.isnan(ctx.ema9):
        ctx.ema9, ctx.ema21, ctx.ema50 = ind.ema9, ind.ema21, ind.ema50
    if math.isnan(ctx.atr):
        ctx.atr = ind.atr
    if math.isnan(ctx.mean_bar_range):
        ctx.mean_bar_range = ind.mean_bar_range
    if math.isnan(ctx.stop_distance):
        ctx.stop_distance = setup.risk

    results = G.run_all(ctx, cfg)
    vetoes = G.vetoes(results)

    decision = Decision(
        verdict="NO TRADE", ticker=ticker, direction=setup.direction, grade=letter,
        missing=missing, guard_vetoes=vetoes, setup=setup, reconciliation=reconciliation,
        why=supporting, against=against,
    )

    # --- a guard veto that expires on a clock is a WAIT, not a NO TRADE
    if vetoes:
        timed = [v for v in vetoes if v.number in TIMED_GUARDS]
        permanent = [v for v in vetoes if v.number not in TIMED_GUARDS]
        if permanent or not timed:
            decision.verdict = "NO TRADE"
            return decision
        decision.verdict = "WAIT"
        decision.wait_until = _clear_time(timed, ctx, cfg, now)
        decision.wait_for = [v.reason for v in timed]
        return decision

    # --- a signal candle still printing is always a WAIT
    if setup.confirmation and not setup.confirmed_closed:
        decision.verdict = "WAIT"
        decision.wait_until = now + timedelta(minutes=5)
        decision.wait_for = [
            f"the {setup.confirmation} to close — a developing candle can flip its shape"
        ]
        return decision

    if letter == "C":
        decision.verdict = "NO TRADE"
        return decision

    if letter == "B" and not cfg["grading"]["b_grade_tradeable"]:
        decision.verdict = "NO TRADE"
        decision.missing.append("B grades are not tradeable under the current config")
        return decision

    if letter == "A" and not cfg["grading"].get("a_grade_tradeable", True):
        decision.verdict = "NO TRADE"
        decision.missing.append("A grades are not tradeable under the current config")
        return decision

    decision.verdict = "TRADE"
    decision.contracts, decision.contract_note = size_position(
        setup, cfg, letter, premium, premium_at_stop
    )
    if decision.contracts == 0:
        decision.verdict = "NO TRADE"
        decision.missing.append("position cannot be sized inside the risk budget")
    return decision


def _clear_time(timed: list[G.GuardResult], ctx: G.GuardContext, cfg: dict,
                now: datetime) -> datetime:
    """When the latest timed veto lifts."""
    candidates = []
    for v in timed:
        if v.number == 2:
            open_dt = datetime.combine(now.astimezone(ET).date(), market.MARKET_OPEN, tzinfo=ET)
            candidates.append(open_dt + timedelta(minutes=cfg["risk"]["opening_lockout_minutes"]))
        elif v.number == 3:
            for ev in ctx.events:
                end = ev.when + timedelta(minutes=cfg["risk"]["event_lockout_after_minutes"])
                if end > now:
                    candidates.append(end)
        elif v.number == 6 and ctx.minutes_since_last_loss is not None:
            remaining = cfg["risk"]["cooldown_minutes_after_loss"] - ctx.minutes_since_last_loss
            candidates.append(now + timedelta(minutes=max(1, remaining)))
    return max(candidates) if candidates else now + timedelta(minutes=15)


# --------------------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------------------

SIGNOFF = "Paper trade. Not advice."
CLOSE_A = "Take the trigger or leave it. No fills in the middle."
CLOSE_OTHER = "No setup, no trade. Patience is the position."


def render(d: Decision, now: Optional[datetime] = None) -> str:
    """Phone-readable. Verdict first, always."""
    if d.verdict == "NO TRADE" and d.no_data_reason:
        return "\n".join([
            f"NO TRADE — {d.ticker} — no data",
            "",
            f"· {d.no_data_reason}",
            "· Not making up a level to fill the gap.",
            "",
            CLOSE_OTHER,
            "",
            SIGNOFF,
        ])

    if d.verdict == "WAIT":
        when = both_tz(d.wait_until) if d.wait_until else "shortly"
        lines = [f"WAIT — send me a screenshot at {when}", "", "WHY"]
        lines += [f"{w}" if w.startswith("·") else f"· {w}" for w in (d.wait_for or d.why)]
        if d.grade and d.setup:
            lines += ["", f"Setup grades {d.grade} as it stands."]
        if d.missing:
            lines += ["", "STILL MISSING"] + [f"· {m}" for m in d.missing]
        lines += ["", CLOSE_OTHER, "", SIGNOFF]
        return "\n".join(lines)

    if d.verdict == "NO TRADE":
        lines = [f"NO TRADE — {d.ticker}", "", "WHY NOT"]
        for v in d.guard_vetoes:
            lines.append(f"· {v.reason}")
        for m in d.missing:
            lines.append(f"· Missing {m}")
        if not d.guard_vetoes and not d.missing:
            # nothing else explained it, so show the evidence that argued against
            for a in d.against:
                lines.append(f"· {a}")
        if d.grade:
            lines += ["", f"Grade {d.grade}."]
        lines += ["", CLOSE_OTHER, "", SIGNOFF]
        return "\n".join(lines)

    s = d.setup
    side = "LONG" if s.direction.startswith("l") else "SHORT"
    lines = [
        f"TRADE — {side} {d.ticker}  ·  Grade {d.grade}",
        "", "WHY",
    ]
    lines += [f"· {w}" for w in d.why]
    if d.against:
        lines += ["", "AGAINST"] + [f"· {a}" for a in d.against]
    lines += [
        "", "THE TRADE",
        f"Underlying entry   {s.entry_low:.2f} – {s.entry_high:.2f}",
        f"Stop (underlying)  {s.stop:.2f}        risk {s.risk:.2f}",
        f"Target 1           {s.target1:.2f}        take 50%",
    ]
    if s.target2:
        lines.append(f"Target 2           {s.target2:.2f}        runner")
    lines += [
        f"Invalidation       any 5m close {'below' if side == 'LONG' else 'above'} {s.stop:.2f}",
        "", "CONTRACT",
        f"{d.ticker} 0DTE {'C' if side == 'LONG' else 'P'} near {s.target1:.0f}  ·  "
        f"{d.contracts} contract{'s' if d.contracts != 1 else ''}",
        d.contract_note,
        "I can't verify a strike, premium, bid, ask or spread from a price chart. Check the chain.",
        "", "EXIT DISCIPLINE",
        "· Hard flat by 14:30 CT / 15:30 ET regardless — 0DTE theta after that is a coin flip",
        "· If it hasn't moved toward T1 in 20 minutes, close it. Dead trade, live theta.",
        "",
        CLOSE_A,
        "", SIGNOFF,
    ]
    return "\n".join(lines)
